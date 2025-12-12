package com.fahribilgen.networkcrm.payload;

import com.fahribilgen.networkcrm.enums.NodeType;
import lombok.Builder;
import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
@Builder
public class NodeClassificationResponse {
    private NodeType suggestedType;
    private double confidence;
    private Map<NodeType, Double> scores;
    private List<String> matchedSignals;
    private String rationale;
}
