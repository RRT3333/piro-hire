# 피로그래밍 지원서 관리 시스템

피로그래밍 동아리의 지원서를 관리하는 웹 애플리케이션입니다.

## 주요 기능

- 📝 지원서 작성 및 제출
  - 이메일 기반 회원가입/로그인
  - 지원자 정보 입력 (이름, 이메일, 전화번호, 프로필 사진)
  - 면접 가능 시간 선택
  - 질문별 답변 작성
  - 임시저장 및 최종제출 기능

- ✉️ 이메일 인증
  - 지원서 제출 시 이메일 인증 필수
  - 6자리 인증코드 발송
  - 인증코드 재발송 기능

- 👥 관리자 기능
  - 모집 기간 설정
  - 면접 기간 설정
  - 지원서 질문 관리
  - 지원자 및 지원서 관리

## 기술 스택

- Backend: Django 5.0.2
- Frontend: Bootstrap 5.3
- Database: SQLite
- Email: SMTP (Gmail/Naver)

## 설치 방법

1. 저장소 클론
```bash
git clone https://github.com/your-username/piro-hire.git
cd piro-hire
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

4. 환경변수 설정
- `.env.example` 파일을 `.env`로 복사하고 필요한 값 설정
```bash
cp .env.example .env
```

5. 데이터베이스 마이그레이션
```bash
python manage.py migrate
```

6. 개발 서버 실행
```bash
python manage.py runserver
```

## 환경변수 설정

`.env` 파일에 다음 환경변수들을 설정해야 합니다:

```plaintext
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 이메일 설정
EMAIL_HOST=smtp.gmail.com  # 또는 smtp.naver.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@example.com
```

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.

## 개발 가이드라인

1. 코드 스타일
   - PEP 8 준수
   - Black 포맷터 사용
   - isort로 import 정렬

2. 커밋 메시지
   - 명확하고 설명적인 커밋 메시지 작성
   - 기능/버그픽스/문서화 등 구분하여 작성

3. 브랜치 전략
   - main: 프로덕션 브랜치
   - develop: 개발 브랜치
   - feature/*: 새로운 기능 개발
   - bugfix/*: 버그 수정

## 문의사항

개발 관련 문의사항은 이슈를 생성해주세요. 