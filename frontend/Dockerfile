FROM node:22-alpine
WORKDIR /app
COPY package.json ./
RUN npm install --include=dev
COPY . .
EXPOSE 3000
CMD ["node", "node_modules/vite/bin/vite.js", "--host", "0.0.0.0"]