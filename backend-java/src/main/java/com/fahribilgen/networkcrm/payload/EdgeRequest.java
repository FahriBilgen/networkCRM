package com.fahribilgen.networkcrm.payload;

import com.fahribilgen.networkcrm.enums.EdgeType;
import lombok.Data;

import java.util.UUID;

@Data
public class EdgeRequest {
    private UUID sourceNodeId;
    private UUID targetNodeId;
    private EdgeType type;
    private Integer weight;
}
