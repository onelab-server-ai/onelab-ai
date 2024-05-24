import json
import traceback

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
import os.path
from pathlib import Path
import joblib
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import badreply
from ai.uil import check_comments
from badreply.models import BadReply
from community.models import Community
from onelab.models import OneLab
from member.models import Member
import random

import os
from pathlib import Path

import joblib
from django.db import transaction
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView

from reply.models import Reply


# class AiView(View):
#     def get(self, request):
#         print("아하하하하하하하ㅏ하ㅏ AI다!!!!!")
#         return render(request, 'main/main-page.html')

class GetRecommendationsAPIView(APIView):

    def get_index_from_member_tag(self, member_tag):
        model_path = os.path.join(Path(__file__).resolve().parent, 'test_onelab.pkl')
        with open(model_path, 'rb') as f:
            model = joblib.load(f)
            print(f'피클 잘 불러옴: {model}')

        onelabs = list(OneLab.objects.filter(tag__tag_name=member_tag))
        onelabs_list = [f"{onelab.onelab_main_title} {onelab.onelab_content} {onelab.onelab_detail_content}" for onelab in onelabs]
        vectorizer = CountVectorizer()
        content_vectors = vectorizer.fit_transform(onelabs_list)
        similarity_matrix = cosine_similarity(content_vectors)
        mean_similarity_scores = np.mean(similarity_matrix, axis=1)

        print(f'평균 유사도 점수 : {mean_similarity_scores}')

        max_similarity_index = np.argmax(mean_similarity_scores)
        print(f'가장 높은 평균 유사도 점수를 가진 OneLab 객체의 인덱스 : {max_similarity_index}')
        return max_similarity_index, content_vectors

    def recommend_similar_onelabs(self, member_tag, content_vectors, num_recommendations=3):
        max_similarity_index, _ = self.get_index_from_member_tag(member_tag)
        similarity_scores = cosine_similarity(content_vectors[max_similarity_index], content_vectors)
        similar_onelab_indices = similarity_scores.argsort()[0]
        print(f'유사도가 높은 순으로 정렬된 인덱스 배열 {similar_onelab_indices}')
        recommended_onelabs = []
        for idx in similar_onelab_indices[::-1]:
            if len(recommended_onelabs) == num_recommendations:
                break
            if idx != max_similarity_index:
                recommended_onelabs.append(OneLab.objects.get(id=idx))

        remaining_recommendations = num_recommendations - len(recommended_onelabs)
        remaining_onelabs = list(OneLab.objects.exclude(id=max_similarity_index).exclude(id__in=[onelab.id for onelab in recommended_onelabs]).order_by('?')[:remaining_recommendations])
        recommended_onelabs.extend(remaining_onelabs)
        return recommended_onelabs

    def get_member_recommendations(self, member_id):
        member = Member.objects.get(id=member_id)
        member_tag = member.tag.tag_name if member.tag else None
        max_similarity_index, content_vectors = self.get_index_from_member_tag(member_tag)
        onelab_tag = OneLab.objects.filter(tag__tag_name=member_tag)
        recommended_onelabs = self.recommend_similar_onelabs(member_tag, content_vectors)
        random_onelab = random.choice(onelab_tag)
        recommended_onelabs.append(random_onelab)
        return recommended_onelabs

    def post(self, request):
        member_id = request.data.get('member_id')
        if not member_id:
            return Response({'error': 'Member ID is required'}, status=400)

        try:
            recommended_onelabs = self.get_member_recommendations(member_id)
        except Member.DoesNotExist:
            return Response({'error': 'Member not found'}, status=404)

        onelab_info = []
        for onelab in recommended_onelabs:
            onelab_files = [file.path for file in onelab.onelabfile_set.all()]
            onelab_info.append({
                'files': onelab_files,
                'onelab_main_title': onelab.onelab_main_title,
                'onelab_content': onelab.onelab_content,
            })

        return Response({'recommended_onelabs': onelab_info}, status=200)

    def get(self, request):
        member_id = request.query_params.get('member_id')
        if not member_id:
            return Response({'error': 'Member ID is required'}, status=400)

        try:
            recommended_onelabs = self.get_member_recommendations(member_id)
        except Member.DoesNotExist:
            return Response({'error': 'Member not found'}, status=404)

        onelab_info = []
        for onelab in recommended_onelabs:
            onelab_files = [file.path for file in onelab.onelabfile_set.all()]
            onelab_info.append({
                'files': onelab_files,
                'onelab_main_title': onelab.onelab_main_title,
                'onelab_content': onelab.onelab_content,
            })

        return Response({'recommended_onelabs': onelab_info}, status=200)

class PredictAPIView(APIView):
        def post(self, request):
            datas = request.data.get('features')
            if not datas:
                return Response({'error': 'Features data is required'}, status=400)

            datas = np.array(datas).astype('float16')
            model_path = os.path.join(Path(__file__).resolve().parent, 'test_onelab.pkl')
            with open(model_path, 'rb') as f:
                model = joblib.load(f)
                print(f'피클 잘 불러옴: {model}')

            predictions = model.predict(datas.reshape(-1, 4))
            probabilities = model.predict_proba(datas.reshape(-1, 4))

            print(f'{predictions}')
            print(f'{probabilities}')

            return Response({
                'predictions': predictions.tolist(),
                'probabilities': probabilities.tolist()
            })

class ReportReplyAPI(APIView):
    def post(self, request):
        data = json.loads(request.body)
        reply_id = data.get('reply_id')

        # 모델소환
        model_file_path = os.path.join(Path(__file__).resolve().parent.parent, 'ai/reviewai.pkl')
        model = joblib.load(model_file_path)

        X_train = [reply_id]

        # 추가 fit
        transformed_X_train = model.named_steps['count_vectorizer'].transform(X_train)
        model.named_steps['multinomial_NB'].partial_fit(transformed_X_train, [1])
        joblib.dump(model, model_file_path)

        # insert
        BadReply.objects.create(comment=X_train[0], target=1)
        Reply.objects.filter(id=reply_id).delete()

        return Response({'reply_id': reply_id})

class PostListView(View):
    def get(self, request):
        return render(request, 'community/community-list.html')


# class ReviewPredictionAPI(APIView):
#     def get(self, request):
#         return render(request, 'community/community-detail.html')
#     def post(self, request):
#         #
#         # 요청 데이터 확인
#
#         # reply_id = data.get('reply_id')
#         # reply_content = data.get("reply-content")
#         data = json.loads(request.body)
#
#         # community_id = data.get('community-id')
#         # reply_content = data.get("reply-content")
#         # data = request.POST
#
#         # data = {
#         #     'reply_content': data['reply_content'],
#         # }
#         community_id = data.get('community-id')
#         reply_content = data.get('reply_content')
#
#         print('fajskfsjkafjsa')
#         print(reply_content)
#         print(community_id)
#
#         result = check_comments(reply_content)
#
#         if result == 'comment':
#             Reply.objects.filter(reply_content=reply_content).delete()
#             # return Response(result)
#             return Response({'result': result})
#
#         return Response({'result': result})


# class ReviewPredictionAPI(APIView):
#     def get(self, request):
#         return render(request, 'community/community-detail.html')
#
#     def post(self, request):
#         try:
#             # 요청 데이터 확인
#             # data = request.POST
#             data = json.loads(request.body)
#
#             # 요청 데이터 출력
#             print('Received request data:', data)
#
#             # community_id와 reply_content 가져오기
#             community_id = data.get('community_id')
#             reply_content = data.get('reply_content')
#
#             print(community_id, reply_content)
#             print('Received community_id:', community_id)
#             print('Received reply_content:', reply_content)
#
#             result = check_comments(reply_content)
#
#             if result == 'comment':
#                 Reply.objects.filter(reply_content=reply_content).delete()
#                 return Response({'result': result})
#
#             return Response({'result': result})
#
#         except Exception as e:
#             print(f"Error: {e}")
#             print(traceback.format_exc())
#             return Response({'error': 'An error occurred'}, status=500)

class ReviewPredictionAPI(APIView):
    def post(self, request):
        try:
            data = json.loads(request.body)
            community_id = data.get('community_id')

            # Community와 Reply 조인하여 reply_content 가져오기
            reply_queryset = Reply.objects.filter(community_id=community_id)



            if reply_queryset.exists():
                reply = reply_queryset.first()  # 첫 번째 댓글 가져오기
                reply_content = reply.reply_content  # 댓글 내용 가져오기

                result = check_comments(reply_content)
                print(result)
                print(reply_content)

                if result == 'comment':
                    Reply.objects.filter(reply_content=reply_content).delete()
                    return Response({'result': result})

                return Response({'result': result})
            else:
                return Response({'result': 'No comments found for this community'}, status=404)

        except Exception as e:
            print(f"Error: {e}")
            print(traceback.format_exc())
            return Response({'error': 'An error occurred'}, status=500)