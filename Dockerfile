FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple -r requirements.txt
CMD ["python", "run.py"]