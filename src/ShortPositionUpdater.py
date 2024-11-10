import os
from datetime import datetime
from io import BytesIO
import uuid

import yaml
import requests
import pandas as pd
from sentence_transformers import SentenceTransformer
from qdrant_client import models, QdrantClient


class ShortPositionAnalyzer:
    def __init__(self, config_path, secrets_path):
        """
        Initialize the ShortPositionAnalyzer with configuration and secrets files.

        :param config_path: Path to the YAML configuration file containing the Excel URL and destination path
        :param secrets_path: Path to the YAML secrets file containing API keys for external services
        """
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        with open(secrets_path, 'r') as file:
            secrets = yaml.safe_load(file)

        self.url = config.get('url')
        self.destfile = config.get('destfile')
        self.news_endpoint = config.get('news_endpoint')

        self.news_api_key = secrets.get('news_api_key')
        self.hugging_face_token = secrets.get('hugging_face_user_token')

        # Initialize Qdrant client and sentence transformer model
        self.qdrant = QdrantClient(":memory:")
        self.COLLECTION_NAME = "Press news"
        self.DISTANCE = models.Distance.COSINE
        self.encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    def download_file(self):
        """
        Download the Excel file from the configured URL and parse its sheets into DataFrames.

        :return: Tuple containing the 'current' and 'historical' DataFrames
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }
        filename = rf'pnc_consob_{datetime.now().strftime("%d-%m-%y")}.xlsx'
        try:
            response = requests.get(self.url, headers=headers, stream=True)
            response.raise_for_status()
            current = pd.read_excel(BytesIO(response.content), engine='openpyxl',
                                    sheet_name=' Correnti - Current ', skiprows=1)
            historical = pd.read_excel(BytesIO(response.content), engine='openpyxl',
                                       sheet_name=' Storiche - Historic ', skiprows=1)
            date_str = pd.read_excel(BytesIO(response.content), engine='openpyxl',
                                     sheet_name=' Pubb. Data - Pubb. Date ', usecols="A").iloc[1].values[0]
            self.pubblication_date = datetime.strptime(date_str, "%d/%m/%Y")
            with open(os.path.join(self.destfile, filename), 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            print(f"File downloaded successfully and saved to {self.destfile}")
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
        return current, historical

    def analyze_positions(self, current, historical):
        """
        Analyze current and historical short positions based on the publication date.

        :param current: DataFrame containing current short positions
        :param historical: DataFrame containing historical short positions
        :return: Tuple containing new positions, closed positions, and grouped positions by asset
        """
        new_positions = current[current['Position Date'] == self.pubblication_date]
        closed_positions = historical[historical['Position Date'] == self.pubblication_date]
        short_positions_by_asset = current.groupby('ISIN').agg(
            {'Position Holder': list, 'Net Short Position (%)': list, 'Share Issuer': 'first'}).reset_index()
        return new_positions, closed_positions, short_positions_by_asset

    def retrieve_news(self, company_name):
        """
        Retrieve the latest news articles for a given company.

        :param company_name: Name of the company for which to retrieve news
        :return: List of tuples containing article titles and URLs
        """
        response = requests.get(self.news_endpoint.format(company_name))
        articles = []
        if response.status_code == 200:
            feed = response.json().get('feed', [])
            articles = [(item['title'], item['url']) for item in feed]
        return articles

    def embed_and_store_news(self, articles):
        """
        Embed news articles and store them in the vector database.

        :param articles: List of tuples containing article titles and URLs
        """
        if not self.qdrant.collection_exists(self.COLLECTION_NAME):
            self.qdrant.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=models.VectorParams(size=self.encoder.get_sentence_embedding_dimension(),
                                                   distance=self.DISTANCE),
            )

        for title, url in articles:
            embedding = self.encoder.encode(title).tolist()
            unique_id = str(uuid.uuid4())
            self.qdrant.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[models.PointStruct(
                    id=unique_id,
                    vector=embedding,
                    payload={"title": title, "url": url}
                )]
            )

    def retrieve_news_with_rag(self, company_name):
        """
        Retrieve latest news for a company and provide an explanation using RAG (Retrieval-Augmented Generation).

        :param company_name: Name of the company for which to retrieve news
        :return: Explanation generated by the language model
        """
        articles = self.retrieve_news(company_name=company_name)
        self.embed_and_store_news(articles)

        query_embedding = self.encoder.encode('Short selling').tolist()
        results = self.qdrant.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_embedding,
            limit=5,
            with_payload=True
        )

        article_summaries = "\n".join(
            [f"Title: {res.payload['title']}" for res in results]
        )

        prompt = (
            f"Based on the following news articles, provide an explanation on why there might be short positions in {company_name}:\n\n"
            f"{article_summaries}\n\n"
        )

        headers = {"Authorization": f"Bearer {self.hugging_face_token}"}
        explanation = requests.post(self.llm_inference_endpoint, headers=headers, json={"inputs": prompt})

        return explanation

    def display_results(self, new_positions, closed_positions, short_positions_by_asset):
        """
        Display the analyzed positions to the console.

        :param new_positions: DataFrame of new short positions
        :param closed_positions: DataFrame of closed short positions
        :param short_positions_by_asset: DataFrame of short positions grouped by asset
        """
        print("New Short Positions:\n", new_positions)
        print("\nClosed Short Positions:\n", closed_positions)
        print("\nShort Positions by Asset:\n", short_positions_by_asset)

    def execute(self):
        """
        Execute the entire analysis process: download data, analyze positions, retrieve news, and display results.
        """
        current, historical = self.download_file()
        new_positions, closed_positions, short_positions_by_asset = self.analyze_positions(current=current,
                                                                                           historical=historical)
        self.retrieve_news_with_rag(company_name='AAPL')
        self.display_results(new_positions=new_positions, closed_positions=closed_positions,
                             short_positions_by_asset=short_positions_by_asset)


analyzer = ShortPositionAnalyzer(config_path="config.yaml", secrets_path="secrets.yaml")
analyzer.execute()
