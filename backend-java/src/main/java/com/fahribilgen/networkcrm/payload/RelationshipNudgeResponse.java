package com.fahribilgen.networkcrm.payload;

import com.fahribilgen.networkcrm.enums.EdgeType;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RelationshipNudgeResponse {

    private List<Nudge> nudges;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Nudge {
        private NodeResponse person;
        private EdgeType edgeType;
        private LocalDate lastInteractionDate;
        private Integer relationshipStrength;
        private String targetName;
        private List<String> reasons;
    }
}
