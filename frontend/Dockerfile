# --- ЕТАП 1: Збірка (Build) ---
# ВИКОРИСТОВУЄМО ВЕРСІЮ 22, бо Vite 6/7 цього вимагає
FROM node:22-alpine as build-stage

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

# --- ЕТАП 2: Продакшн (Nginx) ---
FROM nginx:alpine as production-stage

COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]