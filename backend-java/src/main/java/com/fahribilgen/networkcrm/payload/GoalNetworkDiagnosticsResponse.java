package com.fahribilgen.networkcrm.payload;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class GoalNetworkDiagnosticsResponse {

    private UUID goalId;
    private Readiness readiness;
    private List<String> sectorHighlights;
    private List<String> riskAlerts;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Readiness {
        private String level;
        private double score;
        private String message;
        private List<String> summary;
    }
}
