package com.fahribilgen.networkcrm.payload;

import com.fahribilgen.networkcrm.enums.NodeType;
import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class NodeFilterRequest {
    private NodeType type;
    private List<NodeType> types;
    private String sector;
    private List<String> tags;
    private Integer minRelationshipStrength;
    private Integer maxRelationshipStrength;
    private String searchTerm;
}
