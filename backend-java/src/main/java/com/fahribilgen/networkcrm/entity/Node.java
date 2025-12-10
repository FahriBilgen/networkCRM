package com.fahribilgen.networkcrm.entity;

import com.fahribilgen.networkcrm.enums.NodeType;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@Entity
@Table(name = "nodes")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Node {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private NodeType type;

    @Column(nullable = false)
    private String name;

    @Column(columnDefinition = "TEXT")
    private String description;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private Map<String, Object> properties;

    // Using List<Double> for pgvector embedding, mapped as a simple list for now.
    // In a real pgvector implementation, we might need a custom converter or specific type.
    @JdbcTypeCode(SqlTypes.JSON) 
    // Note: For actual pgvector, we usually use a specific library or native queries.
    // Storing as JSON for MVP simplicity until pgvector-java is fully integrated.
    @Column(columnDefinition = "vector") 
    private List<Double> embedding;
}
