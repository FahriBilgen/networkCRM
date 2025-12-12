package com.fahribilgen.networkcrm.payload;

import com.fahribilgen.networkcrm.enums.EdgeType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NodeProximityResponse {
    private UUID nodeId;
    private int totalConnections;
    private Map<EdgeType, Long> connectionCounts;
    private List<NeighborConnection> neighbors;
    private double influenceScore;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class NeighborConnection {
        private UUID edgeId;
        private EdgeType edgeType;
        private boolean outgoing;
        private NodeResponse neighbor;
        private Integer relationshipStrength;
        private LocalDate lastInteractionDate;
    }
}
