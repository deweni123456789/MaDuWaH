FROM python:3.11-slim

# install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# working directory
WORKDIR /app

# copy project
COPY . .

# install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# run bot
CMD ["python", "main.py"]
