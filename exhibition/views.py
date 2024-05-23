import mimetypes
from urllib.parse import quote

from django.core.paginator import Paginator
from django.utils.encoding import iri_to_uri

from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse

from exhibition.models import Exhibition, ExhibitionFile
from exhibitionMember.models import ExhibitionMember
from file.models import File
from member.models import Member
from school.models import School
from university.models import University
from tag.models import Tag

class ExhibitionWriteView(View):
    def get(self, request):
        return render(request, 'exhibition/write.html')

    @transaction.atomic
    def post(self, request):
        data = request.POST
        files = request.FILES

        member_data = request.session.get('member', {})
        tag_id = member_data.get('tag')
        if tag_id:
            try:
                tag_instance = Tag.objects.get(pk=tag_id)
                member_data['tag'] = tag_instance
            except Tag.DoesNotExist:
                member_data['tag'] = None

        member = Member(**member_data)
        member.save()

        try:
            school = School.objects.get(member=member)
        except School.DoesNotExist:
            # School 객체가 없을 경우 새로운 School 객체를 생성합니다.
            # 적절한 필드를 사용하여 객체를 생성합니다.
            school = School.objects.create(member=member)

        exhibition_data = {
            'exhibition_title': data['exhibition-title'],
            'exhibition_content': data['exhibition-content'],
            'school': school,
            'exhibition_url': data['exhibition-url']
        }

        exhibition = Exhibition.objects.create(**exhibition_data)

        for key, file in files.items():
            file_instance = File.objects.create(file_size=file.size)

            if key == 'upload4':  # upload4 파일이면 download_path 필드에 저장
                ExhibitionFile.objects.create(file=file_instance, path=None, download_path=file, preview=False,
                                              exhibition=exhibition)
            else:
                ExhibitionFile.objects.create(file=file_instance, path=file, download_path=None, preview=key == 'upload1',
                                              exhibition=exhibition)

        return redirect(exhibition.get_absolute_url())

class ExhibitionDetailView(View):
    def get(self, request):
        exhibition_id = request.GET.get('id')
        exhibition = get_object_or_404(Exhibition, id=exhibition_id)
        school = exhibition.school
        member = school.member

        exhibition.exhibition_view_count += 1
        exhibition.save(update_fields=['exhibition_view_count'])

        # 추천 전시회를 가져옵니다
        recommended_exhibitions = get_recommendations(exhibition_id)

        context = {
            'exhibition': exhibition,
            'exhibition_files': list(exhibition.exhibitionfile_set.all()),
            'member_name': member.member_name,
            'exhibitions': recommended_exhibitions
        }

        return render(request, 'exhibition/detail.html', context)

    def post(self, request):
        data = request.POST
        member_id = request.session['member']['id']
        university = University.objects.get(member_id=member_id)

        if university is None:
            return render(request, 'exhibition/detail.html', {'error': '대학생만 참여 가능합니다.'})

        exhibition_id = data.get('id')

        # 이미 참여한 공모전인지 확인
        existing_member = ExhibitionMember.objects.filter(university_id=university.member_id,
                                                          exhibition_id=exhibition_id).first()
        if existing_member:
            # 이미 참여한 경우에는 업데이트 시간만 변경
            from django.utils import timezone
            existing_member.updated_at = timezone.now()
            existing_member.save()
        else:
            # 참여한 공모전이 없는 경우에만 새로운 데이터 생성
            datas = {
                'university_id': university.member_id,
                'exhibition_id': exhibition_id,
                'exhibition_member_status': 0
            }
            ExhibitionMember.objects.create(**datas)

        return redirect('myPage:main')



class ExhibitionFileDownloadView(View):
    def get(self, request, file_path, *args, **kwargs):
        # file_path = file_path.replace('-', '/')
        file_path = file_path
        file_name = file_path.split('/')[-1]
        print('====================')
        print(file_name)
        # file_path: 파일이 있는 경로 설정, 경로에 파일 이름 포함 가능
        fs = FileSystemStorage()
        # fs.open("파일 이름", 'rb')
        content_type, _ = mimetypes.guess_type(file_name)
        response = FileResponse(fs.open(file_path, 'rb'),
                                content_type=content_type)
        # response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        encoded_file_name = quote(file_name)
        print(encoded_file_name)
        response['Content-Disposition'] = f'attachment; filename="{encoded_file_name}"; filename*=UTF-8\'\'{encoded_file_name}'
        return response


class ExhibitionListView(View):
    def get(self, request):
        member_data = request.session.get('member')
        if member_data:
            tag_id = member_data.get('tag')
            if tag_id:
                try:
                    tag_instance = Tag.objects.get(pk=tag_id)
                    member_data['tag'] = tag_instance
                except Tag.DoesNotExist:
                    member_data['tag'] = None
            member = Member(**member_data)
        else:
            member = None

        exhibition_list = Exhibition.enabled_objects.all()
        paginator = Paginator(exhibition_list, 8)  # 페이지당 8개씩
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'page_obj': page_obj,
            'member': member
        }

        return render(request, 'exhibition/list.html', context)



class ExhibitionUpdateView(View):
    def get(self, request, id):
        exhibition = Exhibition.objects.get(id=id)
        exhibitionfiles = ExhibitionFile.objects.filter(exhibition=exhibition)


        context = {
            'exhibition' : exhibition,
            'exhibition_files' : exhibitionfiles,

        }

        return render(request, 'exhibition/update.html', context)

    @transaction.atomic
    def post(self, request, id):
        data = request.POST

        exhibition = Exhibition.objects.get(id=id)
        exhibition.exhibition_title = data['exhibition-title']
        exhibition.exhibition_content = data['exhibition-content']
        exhibition.exhibition_url = data['exhibition-url']

        exhibition.save(update_fields=['exhibition_title', 'exhibition_content', 'exhibition_url'])

        exhibition.exhibitionfile_set.all().delete()

        for key, file in request.FILES.items():
            file_instance = File.objects.create(file_size=file.size)

            if key == 'upload4':  # upload4 파일이면 download_path 필드에 저장
                ExhibitionFile.objects.create(file=file_instance, path=None, download_path=file, preview=False,
                                              exhibition=exhibition)
            else:
                ExhibitionFile.objects.create(file=file_instance, path=file, download_path=None, preview=key=='upload1',
                                              exhibition=exhibition)

        return redirect(exhibition.get_absolute_url())


from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def get_recommendations(exhibition_id, num_recommendations=4):
    # 모든 전시회 데이터를 가져옵니다
    exhibitions = Exhibition.objects.all()

    # 전시회 제목과 내용을 결합하여 수집합니다
    content_list = [
        f"{' '.join(ex.exhibition_title.split()[1:])} {' '.join(ex.exhibition_content.split()[1:5])}"
        for ex in exhibitions
    ]

    # # 전시회 내용을 수집합니다
    # content_list = [ex.exhibition_content for ex in exhibitions]

    # 전시회 제목을 수집합니다
    # content_list = [ex.exhibition_title for ex in exhibitions]

    # CountVectorizer를 사용하여 텍스트 데이터를 벡터화합니다
    vectorizer = CountVectorizer()
    content_vectors = vectorizer.fit_transform(content_list)

    # 코사인 유사도를 계산합니다
    cosine_sim = cosine_similarity(content_vectors, content_vectors)

    # 해당 전시회의 인덱스를 찾습니다
    exhibition_list = list(exhibitions)
    idx = list(exhibitions).index(Exhibition.objects.get(id=exhibition_id))

    # 해당 전시회와 다른 전시회의 유사도를 가져옵니다
    sim_scores = list(enumerate(cosine_sim[idx]))

    # 유사도 점수를 기준으로 정렬합니다
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # 상위 num_recommendations개의 유사한 전시회를 가져옵니다
    sim_scores = sim_scores[1:num_recommendations + 1]  # 첫 번째는 자기 자신이므로 제외합니다
    recommended_indices = [i[0] for i in sim_scores]
    recommended_exhibitions = [exhibitions[i] for i in recommended_indices]

    # 유사도 점수를 소수점 4자리까지 출력
    # for i, score in sim_scores:
    #     print(f"Exhibition ID: {exhibition_list[i].id}, Similarity Score: {score:.4f}")

    return recommended_exhibitions