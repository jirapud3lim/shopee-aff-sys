FROM mcr.microsoft.com/playwright:v1.61.1-noble

WORKDIR /smoke
RUN npm install --no-save playwright@1.61.1
COPY ops/staging/check_manual_handoff.mjs ./
ENV STAGING_WEB_ORIGIN=http://127.0.0.1:3000
CMD ["node", "check_manual_handoff.mjs"]
