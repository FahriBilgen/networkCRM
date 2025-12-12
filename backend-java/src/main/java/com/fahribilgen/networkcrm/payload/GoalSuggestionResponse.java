package com.fahribilgen.networkcrm.payload;

import lombok.Builder;
import lombok.Data;

import java.util.List;
import java.util.UUID;

@Data
@Builder
public class GoalSuggestionResponse {

    private UUID goalId;
    private List<PersonSuggestion> suggestions;

    @Data
    @Builder
    public static class PersonSuggestion {

        private NodeResponse person;
        private double score;
        private String reason;
    }
}
