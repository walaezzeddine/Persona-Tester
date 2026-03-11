import streamlit as st
import asyncio
import json
import sys
import os
import threading
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from src.agent import PersonaAgent
from src.config_loader import Config, load_persona

# ── Page layout ───────────────────────────────────────────────
st.set_page_config(page_title="Persona Tester", layout="wide")
st.title("🧠 Persona Tester — Simulation Comportementale IA")

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.header("Configuration")
url = st.sidebar.text_input("URL cible", value="https://automationexercise.com/products")
objectif = st.sidebar.text_input("Objectif", value="Find the cheapest t-shirt and add it to cart")
persona_choice = st.sidebar.selectbox("Persona", ["acheteur_impatient", "acheteur_prudent", "Les deux"])
launch = st.sidebar.button("🚀 Lancer")


def show_result(result, container):
    container.metric("Statut", result["statut"])
    container.metric("Durée", f"{result['duree_sec']}s")
    container.metric("Produit choisi", result.get("produit", "N/A"))
    container.metric("Prix", result.get("prix", "N/A"))
    container.json(result)


def _run_async(coro):
    """Run an async coroutine from sync code, even if an event loop is already running."""
    result = [None]
    exception = [None]

    def _target():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result[0] = loop.run_until_complete(coro)
        except Exception as e:
            exception[0] = e
        finally:
            loop.close()

    t = threading.Thread(target=_target)
    t.start()
    t.join()
    if exception[0]:
        raise exception[0]
    return result[0]


def run_persona(persona_name, url, objectif, config):
    persona_path = Path(__file__).parent / "personas" / f"{persona_name}.json"
    persona = load_persona(str(persona_path))
    scenario = {"name": objectif, "objectif": objectif}
    agent = PersonaAgent(user=persona, scenario=scenario, config=config)
    return _run_async(agent.run_with_mcp_direct(url=url, objectif=objectif))


if launch:
    config_path = Path(__file__).parent / "config" / "config.yaml"
    config = Config(str(config_path))

    try:
        if persona_choice == "Les deux":
            col1, col2 = st.columns(2)
            col1.subheader("⚡ Acheteur Impatient")
            col2.subheader("🔍 Acheteur Prudent")

            with st.spinner("Running acheteur_impatient..."):
                result1 = run_persona("acheteur_impatient", url, objectif, config)
            show_result(result1, col1)

            with st.spinner("Running acheteur_prudent..."):
                result2 = run_persona("acheteur_prudent", url, objectif, config)
            show_result(result2, col2)

        else:
            st.subheader(f"Persona: {persona_choice}")
            with st.spinner(f"Running {persona_choice}..."):
                result = run_persona(persona_choice, url, objectif, config)
            show_result(result, st)

    except Exception as e:
        st.error(f"Error: {e}")
