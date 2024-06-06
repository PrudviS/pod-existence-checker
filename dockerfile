FROM python:3.8-slim

# Create a non-root user with UID 10001
RUN useradd -m -u 10001 podchecker

USER podchecker

WORKDIR /scripts

COPY src/main.py .

RUN pip install kubernetes
RUN pip install python-dotenv

# unbuffered output
ENV PYTHONUNBUFFERED=1
CMD ["python","-u", "/scripts/main.py"]