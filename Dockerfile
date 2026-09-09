FROM python:3.11-slim
WORKDIR /app
COPY server.py pyproject.toml README.md LICENSE.md ./
RUN pip install --no-cache-dir "fastmcp>=3.1,<4" "web3>=7,<8" eth-abi httpx
ENV HOST=0.0.0.0 PORT=8413
EXPOSE 8413
CMD ["python", "server.py"]
