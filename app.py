"""
Streamlit Web Visualizer for IIT Pokerbots 2026 - Sneak Peek Hold'em.
Run with:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
from engine.game_engine import SneakPeekEngine
from bots.sneak_peek_bot import SneakPeekBot
from bots.baseline_bots import CallStationBot, HonestBidderBot, AggressiveBot
from core.card import Card

st.set_page_config(
    page_title="Sneak Peek Hold'em Visualizer",
    page_icon="🃏",
    layout="wide"
)

# Custom CSS for poker card badges
st.markdown("""
<style>
.card-badge {
    display: inline-block;
    padding: 6px 12px;
    margin: 3px;
    font-size: 18px;
    font-weight: bold;
    border-radius: 8px;
    border: 1px solid #ddd;
    box-shadow: 1px 2px 4px rgba(0,0,0,0.15);
    background-color: white;
}
.suit-red {
    color: #e63946;
}
.suit-black {
    color: #1d3557;
}
.stat-card {
    background-color: #f8f9fa;
    border-radius: 10px;
    padding: 15px;
    border: 1px solid #e9ecef;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

def render_card_html(card_str: str) -> str:
    if not card_str or len(card_str) != 2:
        return ""
    rank, suit = card_str[0], card_str[1]
    suit_symbol = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}.get(suit, suit)
    color_class = "suit-red" if suit in ("h", "d") else "suit-black"
    return f'<span class="card-badge {color_class}">{rank}{suit_symbol}</span>'

def render_cards_list(cards_list: list[str]) -> str:
    return " ".join([render_card_html(c) for c in cards_list])

st.title("🃏 IIT Pokerbots 2026 — Sneak Peek Hold'em Dashboard")
st.markdown("Interactive visualization, match simulator, and hand replayer for the sealed-bid second-price auction poker AI.")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Match Setup")
opp_choice = st.sidebar.selectbox(
    "Select Opponent Baseline",
    ["Calling Station (0-bid leak)", "Honest Bidder (Tight ABC)", "Aggressive Bot (Loose Aggressive)"]
)

num_rounds = st.sidebar.slider(
    "Number of Rounds",
    min_value=5,
    max_value=1000,
    value=50,
    step=25
)

run_button = st.sidebar.button("▶ Run Match Simulation", type="primary", use_container_width=True)

# Session state initialization
if "match_data" not in st.session_state:
    st.session_state["match_data"] = None

if run_button:
    with st.spinner("Running match simulation..."):
        our_bot = SneakPeekBot("SneakPeekAI")
        if "Calling Station" in opp_choice:
            opp_bot = CallStationBot()
        elif "Honest Bidder" in opp_choice:
            opp_bot = HonestBidderBot()
        else:
            opp_bot = AggressiveBot()

        engine = SneakPeekEngine(our_bot, opp_bot, num_rounds=num_rounds, record_history=True)
        results = engine.play_match()
        st.session_state["match_data"] = results

data = st.session_state["match_data"]

if data is not None:
    # --- TOP METRICS ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🏆 Winner", data["winner"])
    with col2:
        st.metric("SneakPeekAI Bankroll", f"{data['bankroll1']:+d} chips")
    with col3:
        st.metric("Opponent Bankroll", f"{data['bankroll2']:+d} chips")
    with col4:
        st.metric("Execution Time", f"{data['time1_seconds']:.3f} s / 20.0s")

    # --- BANKROLL PROGRESSION CHART ---
    st.subheader("📈 Cumulative Bankroll Progression")
    prog = data["bankroll_progression"]
    df_chart = pd.DataFrame({
        "Round": list(range(len(prog))),
        "SneakPeekAI": [p[0] for p in prog],
        data["bot2_name"]: [p[1] for p in prog]
    }).set_index("Round")
    st.line_chart(df_chart, height=320)

    # --- ROUND REPLAYER ---
    st.subheader("🔍 Round-by-Round Hand Inspector")
    history = data["history"]
    if history:
        round_idx = st.slider(
            "Select Round to Inspect",
            min_value=1,
            max_value=len(history),
            value=1
        )
        r_data = history[round_idx - 1]

        # Layout for selected round
        c_cards, c_auction, c_outcome = st.columns([1.5, 1.2, 1.3])

        with c_cards:
            st.markdown("#### 🎴 Cards Dealt")
            st.markdown(f"**SneakPeekAI Hole Cards:** {'(Dealer/SB)' if r_data['bot1_is_sb'] else '(BB)'}")
            st.markdown(render_cards_list(r_data["bot1_cards"]), unsafe_allow_html=True)

            st.markdown(f"**{r_data['bot2_name']} Hole Cards:** {'(BB)' if r_data['bot1_is_sb'] else '(Dealer/SB)'}")
            st.markdown(render_cards_list(r_data["bot2_cards"]), unsafe_allow_html=True)

            st.markdown("**Community Board:**")
            if r_data["community_cards"]:
                st.markdown(render_cards_list(r_data["community_cards"]), unsafe_allow_html=True)
            else:
                st.caption("No community cards dealt (folded preflop).")

        with c_auction:
            st.markdown("#### 🏷 Sneak Peek Auction")
            auc = r_data.get("auction", {})
            if auc:
                b1_bid = auc.get("bot1_bid", 0)
                b2_bid = auc.get("bot2_bid", 0)
                st.write(f"• **SneakPeekAI Bid:** `{b1_bid}` chips")
                st.write(f"• **{r_data['bot2_name']} Bid:** `{b2_bid}` chips")
                st.write(f"• **Auction Winner:** `{auc.get('winner', 'None')}`")
                st.write(f"• **Vickrey Pot Payment:** `{auc.get('payment', 0)}` chips")
                
                rev_card = auc.get("revealed_card")
                if rev_card is not None:
                    card_str = Card.to_str(rev_card)
                    st.markdown(f"• **Revealed Hole Card:** {render_card_html(card_str)}", unsafe_allow_html=True)
                elif "revealed_to_sb" in auc:
                    st.markdown(f"• **Tie Reveal to SB:** {render_card_html(Card.to_str(auc['revealed_to_sb']))}", unsafe_allow_html=True)
                    st.markdown(f"• **Tie Reveal to BB:** {render_card_html(Card.to_str(auc['revealed_to_bb']))}", unsafe_allow_html=True)
            else:
                st.caption("Hand folded before flop auction.")

        with c_outcome:
            st.markdown("#### 💰 Outcome & Profit")
            st.write(f"• **Result:** `{r_data['outcome']}`")
            delta1 = r_data["delta1"]
            st.markdown(f"• **SneakPeekAI Net:** `{'🟢 +' if delta1 >= 0 else '🔴 '}{delta1}` chips")
            st.write(f"• **Bankroll After Round:** `{r_data.get('bankroll1_after', 0)}`")

        # Betting Action Log
        with st.expander("📜 View Full Action-by-Action Log", expanded=False):
            actions = r_data.get("actions", [])
            if actions:
                df_actions = pd.DataFrame(actions)
                st.dataframe(df_actions, use_container_width=True)
            else:
                st.write("No betting actions recorded.")
else:
    st.info("👈 Select match parameters in the sidebar and click **'Run Match Simulation'** to start visualization.")
