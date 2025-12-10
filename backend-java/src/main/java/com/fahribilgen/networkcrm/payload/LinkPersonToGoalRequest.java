package com.fahribilgen.networkcrm.payload;

import lombok.Data;

import java.util.UUID;

@Data
public class LinkPersonToGoalRequest {
    private UUID personId;
    private Double relevanceScore;
    private Integer relationshipStrength;
    private String notes;
    private Boolean addedByUser;
}
