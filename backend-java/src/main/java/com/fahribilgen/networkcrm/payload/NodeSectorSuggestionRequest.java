package com.fahribilgen.networkcrm.payload;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class NodeSectorSuggestionRequest {
    private String name;
    private String description;
    private String notes;
    private List<String> tags;
}
