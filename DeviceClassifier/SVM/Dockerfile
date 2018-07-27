FROM cyberreboot/poseidonml:base
LABEL maintainer="Charlie Lewis <clewis@iqt.org>"

COPY . /SVM
COPY models /models
WORKDIR /SVM

ENTRYPOINT ["python3", "eval_SVM.py"]
