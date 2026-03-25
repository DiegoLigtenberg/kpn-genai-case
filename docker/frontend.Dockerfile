# Frontend: Vite build + serve (static SPA). No nginx — browser calls API via VITE_API_BASE_URL + CORS.
FROM node:20-alpine AS build
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
# Browser-visible API URL baked into JS. Default matches kubectl port-forward ... 8000:8000 from the host.
# Rebuild with --build-arg if the API is reachable at another URL from the browser.
ARG VITE_API_BASE_URL=http://127.0.0.1:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM node:20-alpine
RUN npm install -g serve@14
WORKDIR /app
COPY --from=build /ui/dist ./dist
USER node
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
