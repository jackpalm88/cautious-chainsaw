FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend ./
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY frontend/package.json ./package.json
RUN npm install --omit=dev && npm install -g serve
EXPOSE 5173
CMD ["serve", "-s", "dist", "-l", "5173"]
