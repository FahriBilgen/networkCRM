package com.fahribilgen.networkcrm.payload;

import com.fahribilgen.networkcrm.enums.NodeType;
import lombok.Builder;
import lombok.Data;

import java.util.Map;
import java.util.UUID;

@Data
@Builder
public class NodeResponse {
    private UUID id;
    private NodeType type;
    private String name;
    private String description;
    private Map<String, Object> properties;
}
