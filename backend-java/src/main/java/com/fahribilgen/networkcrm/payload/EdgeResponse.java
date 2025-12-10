package com.fahribilgen.networkcrm.payload;

import com.fahribilgen.networkcrm.enums.EdgeType;
import lombok.Builder;
import lombok.Data;

import java.util.UUID;

@Data
@Builder
public class EdgeResponse {
    private UUID id;
    private UUID sourceNodeId;
    private UUID targetNodeId;
    private EdgeType type;
    private Integer weight;
}
