FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn -q -B dependency:go-offline
COPY src ./src
RUN mvn -q -B -DskipTests package

FROM eclipse-temurin:17-jre-jammy
WORKDIR /app
COPY --from=build /app/target/memlab.jar app.jar
EXPOSE 8080
# ヒープサイズを固定し、エージェント有無の比較で条件を揃える(コンテナのメモリ制限からの
# 自動計算に依存しない)
ENTRYPOINT ["java", "-Xms256m", "-Xmx256m", "-jar", "/app/app.jar"]
