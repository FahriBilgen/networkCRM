package com.fahribilgen.networkcrm.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "favorite_paths")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FavoritePath {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "goal_id", nullable = false)
    private UUID goalId;

    @Column(nullable = false)
    private String label;

    @Column(name = "node_ids", columnDefinition = "TEXT")
    @Convert(converter = JsonAttributeConverter.class)
    private List<UUID> nodeIds;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
