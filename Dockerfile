# Build stage
FROM maven:3.9.9-eclipse-temurin-21-jammy AS builder
WORKDIR /app
COPY backend-java/pom.xml .
RUN mvn dependency:go-offline -q || true
COPY backend-java/src ./src
RUN mvn clean package -q -DskipTests

# Runtime stage
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=builder /app/target/network-crm-0.0.1-SNAPSHOT.jar .
EXPOSE 8080
CMD ["java", "-jar", "network-crm-0.0.1-SNAPSHOT.jar"]
