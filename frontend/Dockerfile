FROM node:20-alpine

WORKDIR /app

# 패키지 파일 복사 및 설치
COPY package*.json ./
RUN npm install

# 소스 코드 복사
COPY . .

# 개발 모드 실행 (프로덕션은 build + start)
EXPOSE 3000

CMD ["npm", "run", "dev"]
