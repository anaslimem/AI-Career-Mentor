FROM python:3.11-slim

WORKDIR /app/frontend

# Install streamlit
RUN pip install --no-cache-dir streamlit python-dotenv requests
# Copy application files
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "main.py", "--server.address=0.0.0.0", "--server.port=8501"]