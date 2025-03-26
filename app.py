import streamlit as st
import requests
from itertools import cycle
import openai
import dotenv
import os

dotenv.load_dotenv()
API_KEY = os.getenv("TRANSCRIPTS_API_KEY")
OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")

st.set_page_config(layout="wide")

def fetch_transcripts_for_ticker(ticker: str,api_key:str) -> list:
    """
    Fetch earnings transcripts for all 4 quarters of 2024 and 2025 for a single ticker.
    Returns a list of transcripts for the given ticker.
    """
    years = [2024, 2025]
    quarters = [1, 2, 3, 4]
    transcripts = []
    api_key = api_key
    
    for year in years:
        for quarter in quarters:
            api_url = f'https://api.api-ninjas.com/v1/earningstranscript?ticker={ticker}&year={year}&quarter={quarter}'
            response = requests.get(api_url, headers={'X-Api-Key': api_key})
            
            if response.status_code == 200:
                try:
                    transcript_data = response.json()
                    if transcript_data and "transcript" in transcript_data:
                        transcript = {
                            "ticker": ticker,
                            "year": year,
                            "quarter": quarter,
                            "content": transcript_data["transcript"],
                            "date": transcript_data.get("date", "N/A")
                        }
                        transcripts.append(transcript)
                except ValueError:
                    pass
    
    return transcripts

st.sidebar.title("📊 Financial Transcript Viewer")

if "selected_tickers" not in st.session_state:
    st.session_state["selected_tickers"] = []  
if "ticker_input_key" not in st.session_state:
    st.session_state["ticker_input_key"] = 0  
if "transcripts_dict" not in st.session_state:
    st.session_state["transcripts_dict"] = {}  
if "selected_transcripts" not in st.session_state:
    st.session_state["selected_transcripts"] = set()
if "analyzed_transcripts" not in st.session_state:
    st.session_state["analyzed_transcripts"] = {}  
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "transcript_summary" not in st.session_state:
    st.session_state["transcript_summary"] = ""
if "show_filter_modal" not in st.session_state:
    st.session_state["show_filter_modal"] = False  
if "filter_companies" not in st.session_state:
    st.session_state["filter_companies"] = set()  
if "filter_years" not in st.session_state:
    st.session_state["filter_years"] = set()  
if "filter_quarters" not in st.session_state:
    st.session_state["filter_quarters"] = set() 

ticker_input = st.sidebar.text_input(
    "Enter Stock Ticker and Press Enter:",
    value="",
    key=f"ticker_input_{st.session_state['ticker_input_key']}"
)

if ticker_input:
    ticker = ticker_input.strip().upper()
    if ticker and ticker not in st.session_state["selected_tickers"]:
        st.session_state["selected_tickers"].append(ticker)
        
        with st.sidebar:
            with st.spinner(f"Fetching transcripts for {ticker}..."):
                transcripts = fetch_transcripts_for_ticker(ticker,API_KEY)
                if transcripts:
                    st.session_state["transcripts_dict"][ticker] = transcripts
                else:
                    st.sidebar.warning(f"No transcripts found for {ticker}.")
                    st.session_state["selected_tickers"].remove(ticker)  
        st.session_state["ticker_input_key"] += 1  
        st.rerun()  

if st.session_state["selected_tickers"]:
    st.sidebar.markdown("**Selected Tickers:**")
    tickers = st.session_state["selected_tickers"]
    num_tickers = len(tickers)
    tickers_per_row = 4  
    num_rows = (num_tickers + tickers_per_row - 1) // tickers_per_row 

    for row in range(num_rows):
        start_idx = row * tickers_per_row
        end_idx = min(start_idx + tickers_per_row, num_tickers)
        row_tickers = tickers[start_idx:end_idx]
        
        cols = st.sidebar.columns(len(row_tickers))
        for idx, ticker in enumerate(row_tickers):
            with cols[idx]:
                if st.button(f"{ticker} ✖️", key=f"remove_{ticker}_{start_idx + idx}", use_container_width=True):
                    st.session_state["selected_tickers"].remove(ticker)
                    if ticker in st.session_state["transcripts_dict"]:
                        del st.session_state["transcripts_dict"][ticker]
                    st.session_state["selected_transcripts"] = {
                        label for label in st.session_state["selected_transcripts"]
                        if not label.startswith(f"{ticker} ")
                    }
                    if not st.session_state["transcripts_dict"]:
                        st.session_state["chat_history"] = []
                        st.session_state["transcript_summary"] = ""
                        st.session_state["analyzed_transcripts"] = {}
                    st.rerun()  

search_query = st.sidebar.text_input("Search Transcript:")

selected_transcripts = st.session_state["selected_transcripts"]

if st.session_state["transcripts_dict"]:
    all_transcripts = []
    for ticker, transcripts in st.session_state["transcripts_dict"].items():
        all_transcripts.extend(transcripts)
    
    if search_query:
        all_transcripts = [t for t in all_transcripts if search_query.lower() in t["content"].lower()]
    
    col1, col2 = st.columns([8, 1])
    with col1:
        st.subheader("Available Transcripts")
    with col2:
        if st.button("Filter", key="filter_available_transcripts"):
            st.session_state["show_filter_modal"] = not st.session_state["show_filter_modal"]

    if st.session_state["show_filter_modal"]:
        with st.expander("Filter Options", expanded=True):
            st.markdown("**Select Companies:**")
            companies = sorted({transcript["ticker"] for transcript in all_transcripts})
            for company in companies:
                if st.checkbox(company, value=(company in st.session_state["filter_companies"]), key=f"filter_company_{company}"):
                    st.session_state["filter_companies"].add(company)
                else:
                    st.session_state["filter_companies"].discard(company)

            st.markdown("**Select Years:**")
            years = sorted({transcript["year"] for transcript in all_transcripts})
            for year in years:
                if st.checkbox(str(year), value=(year in st.session_state["filter_years"]), key=f"filter_year_{year}"):
                    st.session_state["filter_years"].add(year)
                else:
                    st.session_state["filter_years"].discard(year)

            st.markdown("**Select Quarters:**")
            quarters = sorted({transcript["quarter"] for transcript in all_transcripts})
            for quarter in quarters:
                if st.checkbox(f"Q{quarter}", value=(quarter in st.session_state["filter_quarters"]), key=f"filter_quarter_{quarter}"):
                    st.session_state["filter_quarters"].add(quarter)
                else:
                    st.session_state["filter_quarters"].discard(quarter)

            if st.button("Apply Filters"):
                st.session_state["show_filter_modal"] = False
                st.rerun()

    filtered_transcripts = all_transcripts
    if st.session_state["filter_companies"]:
        filtered_transcripts = [t for t in filtered_transcripts if t["ticker"] in st.session_state["filter_companies"]]
    if st.session_state["filter_years"]:
        filtered_transcripts = [t for t in filtered_transcripts if t["year"] in st.session_state["filter_years"]]
    if st.session_state["filter_quarters"]:
        filtered_transcripts = [t for t in filtered_transcripts if t["quarter"] in st.session_state["filter_quarters"]]

    if filtered_transcripts:
        transcripts_by_ticker = {}
        for transcript in filtered_transcripts:
            ticker = transcript["ticker"]
            if ticker not in transcripts_by_ticker:
                transcripts_by_ticker[ticker] = []
            transcripts_by_ticker[ticker].append(transcript)
        
        for ticker, transcripts in transcripts_by_ticker.items():
            st.markdown(f"### {ticker}")
            cols = cycle(st.columns(4))  
            for transcript in transcripts:
                col = next(cols)
                label = f"{transcript['ticker']} FY{transcript['year']} Q{transcript['quarter']} ({transcript['date']})"
                with col:
                    if col.button(f"FY{transcript['year']} Q{transcript['quarter']} ({transcript['date']})", key=f"btn_{label}", use_container_width=True):
                        if label in selected_transcripts:
                            selected_transcripts.remove(label)
                        else:
                            selected_transcripts.add(label)
        
        st.session_state["selected_transcripts"] = selected_transcripts
    else:
        st.markdown("**No transcripts match the selected filters.**")
else:
    st.subheader("Available Transcripts")
    st.markdown("**No transcripts selected**")

st.sidebar.subheader("📜 Selected Transcripts")
if selected_transcripts:
    for label in selected_transcripts:
        st.sidebar.text(label)
else:
    st.sidebar.text("None selected")

if selected_transcripts:
    transcript_data = ""
    
    selected_by_ticker = {}
    for label in selected_transcripts:
        transcript = next((t for t in all_transcripts if f"{t['ticker']} FY{t['year']} Q{t['quarter']} ({t['date']})" == label), None)
        if transcript:
            ticker = transcript["ticker"]
            if ticker not in selected_by_ticker:
                selected_by_ticker[ticker] = []
            selected_by_ticker[ticker].append(transcript)
            transcript_data += transcript["content"] + "\n\n"

    # Display transcripts grouped by ticker
    # for ticker, transcripts in selected_by_ticker.items():
    #     st.markdown(f"### {ticker}")
    #     for transcript in transcripts:
    #         label = f"FY{transcript['year']} Q{transcript['quarter']} ({transcript['date']})"
    #         st.markdown(f"#### {label}")
    #         st.text_area("", transcript["content"], height=300, key=f"transcript_{ticker}_{label}")

if selected_transcripts:
    new_transcripts = {}
    for label in selected_transcripts:
        transcript = next((t for t in all_transcripts if f"{t['ticker']} FY{t['year']} Q{t['quarter']} ({t['date']})" == label), None)
        if transcript and label not in st.session_state["analyzed_transcripts"]:
            new_transcripts[label] = transcript["content"]

if selected_transcripts:
    st.subheader("💬 Chat with AI about Selected Transcripts")

    client = openai.OpenAI(api_key=OPEN_AI_API_KEY)
    
    if new_transcripts:
        with st.spinner("AI is analyzing new transcripts..."):
            for label, content in new_transcripts.items():
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Read the following earnings call transcript and analyze the company's performance:"},
                        {"role": "user", "content": content}
                    ]
                )
                summary = response.choices[0].message.content

                st.session_state["transcript_summary"] += f"\n\n{summary}"
                st.session_state["analyzed_transcripts"][label] = summary  

    chat_container = st.container()

    with chat_container:
        for user_query, ai_response in st.session_state["chat_history"]:
            with st.chat_message("user"):
                st.markdown(f"{user_query}")
            with st.chat_message("assistant"):
                st.markdown(f"{ai_response}")

    user_query = st.chat_input("Ask questions about the selected transcripts:")

    if user_query:
        with chat_container:
            with st.chat_message("user"):
                st.markdown(f"{user_query}")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Your job is to answer questions based on the information provided of the selected earnings calls. For any informatino you provide, if there's a related data point, try to always disclose it in your answer."},
                {"role": "system", "content": st.session_state["transcript_summary"]},  
                {"role": "user", "content": user_query}
            ]
        )
        answer = response.choices[0].message.content

        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(f"{answer}")

        st.session_state["chat_history"].append((user_query, answer))