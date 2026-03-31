import streamlit as st
import google.generativeai as genai
import json
import base64
from PIL import Image
import os

st.set_page_config(
    page_title="NUTRI-ORACLE",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for dark oracle theme
st.markdown("""
<style>
    .stApp {
        background-color: #050508;
    }
    h1, h2, h3 {
        font-family: serif !important;
        color: #00e5a0 !important;
    }
    .stButton>button {
        color: #00e5a0;
        border-color: #00e5a0;
        background-color: rgba(0, 229, 160, 0.1);
        text-transform: uppercase;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #00e5a0;
        color: #050508;
        box-shadow: 0 0 15px rgba(0,229,160,0.4);
    }
</style>
""", unsafe_allow_html=True)

st.title("⬡ NUTRI-ORACLE")
st.caption("The Oracle Sees What You Cannot")

# Setup Gemini
try:
    api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
except Exception:
    api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
else:
    st.warning("⚠️ No GEMINI_API_KEY found in Streamlit Secrets or Environment Variables.")

def fetch_oracle_response(ingredients, age, goal):
    system_prompt = """You are NUTRI-ORACLE, a brutally honest nutritional intelligence system. Given a list of ingredients a person has at home, respond ONLY in valid JSON exactly in this structure:
{
  "vitality_score": integer 0-100,
  "deficiencies": array of strings (nutrients lacking),
  "health_risks": array of objects each with {"risk": string, "severity": "low"/"medium"/"high", "timeline": string, "prevention": string},
  "survival_recipes": array of 3 objects each with {"name": string, "ingredients_used": array, "steps": array, "health_benefit": string, "prep_time": string},
  "body_timeline": {"7_days": string, "30_days": string, "6_months": string},
  "meal_plan": {"breakfast": {"meal": string, "ingredients_from_your_kitchen": array, "why": string}, "lunch": {"meal": string, "ingredients_from_your_kitchen": array, "why": string}, "dinner": {"meal": string, "ingredients_from_your_kitchen": array, "why": string}, "snack": {"meal": string, "ingredients_from_your_kitchen": array, "why": string}},
  "oracle_verdict": string,
  "aura_color": string
}"""
    prompt = f"Ingredients: {', '.join(ingredients)}\nAge: {age}\nGoal: {goal}"
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_prompt)
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
            
        return json.loads(text.strip())
    except Exception as e:
        st.error(f"Oracle observation failed: {e}")
        return None

def analyze_image(img):
    try:
        vision_model = genai.GenerativeModel('gemini-1.5-flash')
        vision_prompt = "List every food item you can see in this image. Return ONLY a JSON array of ingredient name strings."
        response = vision_model.generate_content([vision_prompt, img])
        text = response.text.strip()
        
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
            
        return json.loads(text.strip())
    except Exception as e:
        st.error("The Oracle could not decipher the visual offering.")
        return []

tab1, tab2 = st.tabs(["TYPE INGREDIENTS", "SCAN YOUR FRIDGE"])

with tab1:
    ingredients_input = st.text_area("Enter ingredients separated by commas", placeholder="e.g. rice, eggs, tomatoes, onion")
    col1, col2 = st.columns(2)
    age = col1.number_input("Age", min_value=1, max_value=120, value=25)
    goal = col2.selectbox("Goal", ["balanced", "weight-loss", "muscle-gain", "energy-boost"])
    
    if st.button("CONSULT THE ORACLE →", key="btn_type"):
        if not ingredients_input:
            st.warning("Please enter ingredients first.")
        else:
            with st.spinner("Oracle is reading your kitchen..."):
                ingredients_list = [x.strip() for x in ingredients_input.split(",") if x.strip()]
                data = fetch_oracle_response(ingredients_list, age, goal)
                st.session_state['oracle_data'] = data

with tab2:
    uploaded_file = st.file_uploader("Drop your fridge photo here", type=["jpg", "jpeg", "png", "webp"])
    if st.button("CONSULT THE ORACLE →", key="btn_scan"):
        if not uploaded_file:
            st.warning("Please upload an image first.")
        else:
            with st.spinner("Oracle is deciphering your visual offering..."):
                img = Image.open(uploaded_file)
                ingredients_list = analyze_image(img)
                if ingredients_list:
                    st.success(f"Discovered: {', '.join(ingredients_list)}")
                    data = fetch_oracle_response(ingredients_list[:50], 25, "balanced")
                    st.session_state['oracle_data'] = data
                else:
                    st.error("No ingredients found.")

if 'oracle_data' in st.session_state and st.session_state['oracle_data']:
    d = st.session_state['oracle_data']
    st.markdown("---")
    
    aura = d.get('aura_color', '#00e5a0')
    verdict = d.get('oracle_verdict', '...')
    
    st.markdown(f"""
    <div style="background: radial-gradient(circle, {aura} 0%, transparent 100%); padding: 30px; text-align: center; border-radius: 12px; border: 1px solid {aura}; margin-bottom: 20px;">
        <h2 style="color: white !important; margin: 0; text-shadow: 0 2px 10px rgba(0,0,0,0.8);">{verdict.upper()}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    colA, colB, colC = st.columns(3)
    colA.metric("Vitality Score", f"{d.get('vitality_score', 0)}/100")
    colB.metric("Health Risks", len(d.get('health_risks', [])))
    colC.metric("Recipes Found", len(d.get('survival_recipes', [])))
    
    st.subheader("⚠ WHAT YOUR BODY IS MISSING")
    defs = d.get('deficiencies', [])
    if defs:
        tags = "".join([f'<span style="background: rgba(255,170,0,0.2); color: #ffaa00; padding: 5px 10px; border-radius: 15px; margin-right: 10px;">{x}</span>' for x in defs])
        st.markdown(tags, unsafe_allow_html=True)
    else:
        st.info("No immediate deficiencies detected... yet.")
    
    st.markdown("---")
    st.subheader("☠ YOUR BODY'S FUTURE IF YOU CONTINUE")
    for r in d.get('health_risks', []):
        color = "red" if r.get('severity') == "high" else "orange" if r.get('severity') == "medium" else "green"
        st.markdown(f"**<span style='color:{color}'>{r.get('severity', 'low').upper()}</span> | {r.get('risk', '')}** (in {r.get('timeline', '')})  \n*Prevention:* {r.get('prevention', '')}", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🍳 WHAT YOU CAN MAKE RIGHT NOW")
    for r in d.get('survival_recipes', []):
        with st.expander(f"**{r.get('name', 'Recipe')}** (⏱️ {r.get('prep_time', 'N/A')})"):
            st.markdown(f"**Benefit:** {r.get('health_benefit', 'N/A')}")
            st.markdown(f"**Uses:** {', '.join(r.get('ingredients_used', []))}")
            for i, step in enumerate(r.get('steps', [])):
                st.markdown(f"{i+1}. {step}")

    st.markdown("---")
    st.subheader("📅 YOUR BODY OVER TIME")
    bt = d.get('body_timeline', {})
    c1, c2, c3 = st.columns(3)
    c1.info(f"**7 Days:**\n\n{bt.get('7_days', bt.get('7 days', ''))}")
    c2.warning(f"**30 Days:**\n\n{bt.get('30_days', bt.get('30 days', ''))}")
    c3.error(f"**6 Months:**\n\n{bt.get('6_months', bt.get('6 months', ''))}")

    st.markdown("---")
    st.subheader("🗓 ORACLE'S DAILY PLAN FOR YOU")
    mp = d.get('meal_plan', {})
    for meal_type, meal_info in mp.items():
        st.markdown(f"**{str(meal_type).upper()}:** {meal_info.get('meal')}  \n*Why:* {meal_info.get('why')}  \n*Ingredients:* {', '.join(meal_info.get('ingredients_from_your_kitchen', []))}")
