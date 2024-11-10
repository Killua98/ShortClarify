# 📉 ShortPositionAnalyzer

**ShortPositionAnalyzer** is a Python tool designed to provide deep insights into short positions by combining the latest data from regulatory sources with contextual information from recent news articles. Using a Retrieval-Augmented Generation (RAG) approach, it delivers explanations for confirmed short positions, helping users understand the market dynamics driving these positions.

## 🚀 Features

- **📊 Download and Analyze Short Positions**  
   Automatically retrieves and processes short position data from CONSOB's public disclosures.
   
- **📰 Retrieve Relevant News**  
   Gathers the latest news articles related to specified companies to gauge market sentiment.

- **🔍 Vector Embedding & Storage**  
   Embeds news articles into vector representations and stores them in a vector database, enabling efficient similarity searches for relevant news.

- **💡 Retrieval-Augmented Generation (RAG)**  
   Uses an LLM to generate contextual insights based on retrieved news articles, offering explanations for why a company may have been shorted. This includes highlighting market conditions, notable events, or trends that might have influenced shorting activity.

- **📈 Display Comprehensive Results**  
   Outputs analyzed data, such as new and closed short positions and summaries of short positions grouped by asset.

## 🌱 Future Improvements

This project is in its early stages, and several enhancements are planned to increase its functionality and accuracy:

- **🧠 Advanced NLP Models**  
   Explore and integrate more sophisticated LLMs to improve the quality of generated explanations.

- **💻 Enhanced User Interface**  
   Develop an intuitive dashboard or web interface for a seamless data visualization and exploration experience.

- **⏰ Scheduled Automation**  
   Implement a scheduling system for automatic retrieval, analysis, and updates of short position data and explanations at specified intervals.

- **🤝 Investment Tracker Integration**  
   Enable integration with self-hosted investment trackers (e.g., Ghostfolio) to alert users if any companies in their portfolio have been targeted by short sellers.

---

