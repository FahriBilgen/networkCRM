package com.fahribilgen.networkcrm.payload;

import com.fahribilgen.networkcrm.enums.EdgeType;
import lombok.Data;

import java.time.LocalDate;
import java.util.UUID;

@Data
public class EdgeRequest {
    private UUID sourceNodeId;
    private UUID targetNodeId;
    private EdgeType type;
    private Integer weight;
    private Integer relationshipStrength;
    private String relationshipType;
    private LocalDate lastInteractionDate;
    private Double relevanceScore;
    private Boolean addedByUser;
    private String notes;
    private Integer sortOrder;
}
