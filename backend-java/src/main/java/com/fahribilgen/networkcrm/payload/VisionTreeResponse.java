package com.fahribilgen.networkcrm.payload;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class VisionTreeResponse {
    private List<VisionNode> visions;

    @Data
    @Builder
    public static class VisionNode {
        private NodeResponse vision;
        private List<GoalNode> goals;
    }

    @Data
    @Builder
    public static class GoalNode {
        private NodeResponse goal;
        private List<NodeResponse> projects;
    }
}
