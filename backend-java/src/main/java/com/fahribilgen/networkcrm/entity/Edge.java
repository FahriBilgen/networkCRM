package com.fahribilgen.networkcrm.entity;

import com.fahribilgen.networkcrm.enums.EdgeType;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

@Entity
@Table(name = "edges")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Edge {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "source_node_id", nullable = false)
    private Node sourceNode;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "target_node_id", nullable = false)
    private Node targetNode;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private EdgeType type;

    @Column(nullable = false)
    private Integer weight; // 0-5
}
