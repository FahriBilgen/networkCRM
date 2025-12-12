package com.fahribilgen.networkcrm.entity;

import com.fahribilgen.networkcrm.enums.NodeType;
import com.fahribilgen.networkcrm.enums.ProjectStatus;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;

import java.time.LocalDate;
import java.time.LocalDateTime;
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

    private String sector;

    @ElementCollection
    @CollectionTable(name = "node_tags", joinColumns = @JoinColumn(name = "node_id"))
    @Column(name = "tag")
    private List<String> tags;

    @Column(name = "relationship_strength")
    private Integer relationshipStrength;

    private String company;

    private String role;

    @Column(name = "linkedin_url")
    private String linkedinUrl;

    @Column(columnDefinition = "TEXT")
    private String notes;

    private Integer priority;

    private LocalDate dueDate;

    private LocalDate startDate;

    private LocalDate endDate;

    @Enumerated(EnumType.STRING)
    private ProjectStatus status;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @Column(columnDefinition = "TEXT")
    @Convert(converter = JsonAttributeConverter.class)
    private Map<String, Object> properties;

    @Column(columnDefinition = "TEXT")
    @Convert(converter = JsonAttributeConverter.class)
    private List<Double> embedding;
}
