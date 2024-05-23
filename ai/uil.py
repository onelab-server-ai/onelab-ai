import os
from pathlib import Path

import joblib
from django.http import JsonResponse
from django.views import View
from rest_framework.utils import json

from badreply.models import BadReply


def check_comments(content):
    result = 'success'

    # 모델소환
    model_file_path = os.path.join(Path(__file__).resolve().parent.parent, 'ai/reviewai.pkl')
    model = joblib.load(model_file_path)

    X_train = [content]
    prediction = model.predict(X_train)
    print("들어옴!!!")
    print(X_train)

    if prediction[0] == 1:
        # 추가 fit
        transformed_X_train = model.named_steps['count_vectorizer'].transform(X_train)
        model.named_steps['multinomial_NB'].partial_fit(transformed_X_train, [1])
        joblib.dump(model, model_file_path)

        # insert
        BadReply.objects.create(comment=X_train[0], target=1)
        result = 'comment'

    return result






