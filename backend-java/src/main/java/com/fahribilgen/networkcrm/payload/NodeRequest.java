package com.fahribilgen.networkcrm.payload;

import com.fahribilgen.networkcrm.enums.NodeType;
import lombok.Data;

import java.util.Map;

@Data
public class NodeRequest {
    private NodeType type;
    private String name;
    private String description;
    private Map<String, Object> properties;
}
