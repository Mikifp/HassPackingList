ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3

COPY run.sh /run.sh
COPY server.py seed.py /app/
COPY web /app/web

RUN chmod a+x /run.sh
CMD [ "/run.sh" ]
