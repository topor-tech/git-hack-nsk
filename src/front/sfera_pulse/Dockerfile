FROM node:20-alpine AS build-env
COPY . /app
WORKDIR /app
RUN npm ci
RUN npm run build

FROM node:20-alpine as prod
COPY ./package.json package-lock.json /app/
WORKDIR /app
RUN npm ci
COPY --from=build-env /app/dist /app/dist
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "3000"]