package com.fahribilgen.networkcrm.payload;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class NodeSectorSuggestionResponse {
    private String sector;
    private double confidence;
    private List<String> matchedKeywords;
    private String rationale;
}
