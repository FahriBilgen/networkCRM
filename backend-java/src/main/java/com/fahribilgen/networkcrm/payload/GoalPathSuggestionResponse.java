package com.fahribilgen.networkcrm.payload;

import lombok.Builder;
import lombok.Data;

import java.util.List;
import java.util.UUID;

@Data
@Builder
public class GoalPathSuggestionResponse {
    private UUID goalId;
    private List<PathSuggestion> suggestions;

    @Data
    @Builder
    public static class PathSuggestion {
        private NodeResponse person;
        private int distance;
        private List<UUID> pathNodeIds;
    }
}
