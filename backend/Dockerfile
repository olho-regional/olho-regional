FROM ghcr.io/tursodatabase/libsql-server:latest

EXPOSE 8080 5001

VOLUME /var/lib/sqld

CMD ["sqld", "--db-path", "/var/lib/sqld/data.sqld", "--http-listen-addr", "0.0.0.0:8080", "--grpc-listen-addr", "0.0.0.0:5001"]
