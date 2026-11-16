#  Sign-In Travel Assistant with RAG Chat (Lumen Travel)

**University of Science, VNU-HCM — Faculty of Information Technology**  
**Course:** Computational Thinking — Practice 03  

---

## 1. Student Information & Chosen City

- **Student Name:** Lưu Minh Tiến *(25127242)*
- **GitHub Account:** [TienLuu2007](https://github.com/TienLuu2007)
- **Chosen City:** **Ho Chi Minh City, Vietnam** (`knowledge_base.json` contains 15 curated entries `G01`–`G15` covering museums, markets, landmarks, viewpoints, parks, pagodas, walking streets, river transport, airport buses, and seasonal tips).

---

## 2. Project Structure

```text
SIGN-IN-TRAVEL-ASSISTANT-WITH-RAG-CHAT/
├── app.py                  # Streamlit UI (Firebase Auth screen + RAG Chat view)
├── firebase_client.py      # Firebase Authentication REST API client (sign-up & sign-in)
├── rag.py                  # RAG pipeline (embeddinggemma, cosine similarity, qwen3:4b)
├── knowledge_base.json     # 15 travel guide entries (G01–G15) for Ho Chi Minh City
├── requirements.txt        # Python package dependencies
├── .env.example            # Template for environment variables (empty values)
├── .gitignore              # Ensures .env and cache files are never committed
└── README.md               # Documentation, CT analysis, and test table
```

---

## 3. Setup & Running Instructions

### Step 1: Clone the Repository & Install Dependencies

```bash
git clone https://github.com/TienLuu2007/SIGN-IN-TRAVEL-ASSISTANT-WITH-RAG-CHAT.git
cd SIGN-IN-TRAVEL-ASSISTANT-WITH-RAG-CHAT

# (Optional) Create and activate a virtual environment
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure `.env`

Copy `.env.example` to `.env` and fill in your credentials (never commit `.env`):

```bash
cp .env.example .env
```

Edit `.env`:

```env
FIREBASE_API_KEY=your_firebase_web_api_key_here
OLLAMA_URL=https://your-tunnel-url.a.free.pinggy.link
```

- Make sure your Ollama server (from Lab 4) has both required models pulled:
  ```bash
  ollama pull embeddinggemma
  ollama pull qwen3:4b
  ```

### Step 3: Run the Streamlit Application

```bash
streamlit run app.py
```

---

## 4. Test Table

Below is the evaluation across **8 test questions** (3 directly answerable, 1 paraphrase, 2 not in the guide, plus 2 edge cases demonstrating **Missing Data** and **Retrieval** limitations):

| # | Type | Question | Expected Entry ID | Retrieved Top-3 IDs | Assistant Answer Summary | Correct? | Where It Failed (if wrong) |
| :-: | :--- | :--- | :---: | :---: | :--- | :-: | :--- |
| **1** | **Answerable (1)** | *"What are the opening hours and ticket prices for Independence Palace?"* | `[G01]` | `[G01]`, `[G02]`, `[G09]` | Open daily 8:00 AM – 3:30 PM; tickets cost 40,000 VND for adults and 20,000 VND for students `[G01]`. | ✅ Yes | *None (Succeeded)* |
| **2** | **Answerable (2)** | *"How can I get from Tan Son Nhat Airport to District 1 by public bus?"* | `[G11]` | `[G11]`, `[G10]`, `[G01]` | Take yellow public Bus 152 (5,000 VND, 5:30 AM – 7:00 PM) or Bus 109 (15,000 VND, 5:45 AM – 11:40 PM) `[G11]`. | ✅ Yes | *None (Succeeded)* |
| **3** | **Answerable (3)** | *"When do the street food stalls at Ho Thi Ky Flower Market open and how much do dishes cost?"* | `[G07]` | `[G07]`, `[G03]`, `[G06]` | Flower stalls open 24h; street food vendors run 3:00 PM – 11:00 PM with dishes from 25,000 to 60,000 VND `[G07]`. | ✅ Yes | *None (Succeeded)* |
| **4** | **Paraphrase** | *"How much does it cost to take a boat ride along the river from Bach Dang, and when do the boats run?"* | `[G10]` | `[G10]`, `[G05]`, `[G13]` | A one-way ticket on the Saigon Waterbus is 15,000 VND per passenger, operating between 7:00 AM and 9:00 PM `[G10]`. | ✅ Yes | *None (Succeeded)* |
| **5** | **Not in Guide (1)** | *"What is the ticket price for Dam Sen Water Park?"* | *None* (`"I don't know"`) | `[G08]`, `[G10]`, `[G05]` | `"I don't know based on the travel guide."` | ✅ Yes | *None (Correctly abstained)* |
| **6** | **Not in Guide (2)** | *"Which beach resort in Ho Chi Minh City has the best surfing lessons?"* | *None* (`"I don't know"`) | `[G12]`, `[G10]`, `[G08]` | `"I don't know based on the travel guide."` | ✅ Yes | *None (Correctly abstained)* |
| **7** | **Failure Analysis (Missing Data)** | *"Can I rent an audio guide at Independence Palace, and how much is it?"* | `[G01]` *(lacks audio guide info)* | Top-3 includes `[G02]` & `[G01]` | `"I don't know based on the travel guide."` | ⚠️ Abstains (No audio guide info) | **Missing Data** (plus **Retrieval** competition): `[G01]` does not mention audio guides (*missing data*), while `[G02]` ranks high in *retrieval* due to `"audio guides can be rented for an extra 80,000 VND"`. Thanks to `temperature=0.0` and the strict prompt, `qwen3:4b` refuses to mix `[G02]` into `[G01]`. |
| **8** | **Failure Analysis (Retrieval `k=3`)** | *"Which places in the guide have free entry?"* | `[G03]`, `[G04]`, `[G13]`, `[G14]` | Only 3 of the 4 entries fit in `top-3` | Lists at most the 3 retrieved entries and omits at least one valid entry (e.g., `[G13]` free stairs or `[G03]`/`[G04]`/`[G14]`). | ❌ Incomplete | **Retrieval** (`k = 3` cap): 4 guide entries mention `"free"` (`[G03]`, `[G04]`, `[G13]`, `[G14]`), so retrieving `top-3` drops at least one relevant entry before generation. |

---

## 5. Known Limitations & AI Tools Used

### Known Limitations
1. **Session Persistence:** By assignment specification, chat history is stored strictly in `st.session_state` (RAM) without Firestore or an external database, so refreshing the browser tab resets the current session.
2. **Pinggy Free Tunnel Latency & Expiry:** Free Pinggy URLs expire after ~60 minutes and introduce network latency when calling `qwen3:4b` remotely. If the tunnel resets, `OLLAMA_URL` in `.env` must be updated.
3. **Small Static Knowledge Base:** The assistant only knows facts from the 15 entries (`G01`–`G15`) in `knowledge_base.json` and intentionally refuses to answer broader Ho Chi Minh City questions outside the guide.

### Note on AI Tools Used
- **AI Assistance:** Gemini (Google Antigravity) was used to help structure the Streamlit UI components, refine error handling for Firebase REST API and Ollama/Pinggy requests, and format the README documentation and Mermaid diagram. All knowledge base entries (`G01`–`G15`) and test scenarios were reviewed and verified against the assignment rubric.

---

## 6. Demonstration Video

- **Video Link:** `https://drive.google.com/file/d/1MTim2ATGE3kfh8PvC58cuBGc-LIgQVOJ/view?usp=drive_link`
