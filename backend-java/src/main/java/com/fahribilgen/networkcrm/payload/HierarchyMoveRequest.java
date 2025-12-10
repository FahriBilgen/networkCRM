package com.fahribilgen.networkcrm.payload;

import lombok.Data;

import java.util.UUID;

@Data
public class HierarchyMoveRequest {
    private UUID targetNodeId;
    private Integer sortOrder;
}
