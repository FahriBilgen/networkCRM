package com.fahribilgen.networkcrm.payload;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class GraphResponse {
    private List<NodeResponse> nodes;
    private List<EdgeResponse> links;
}
