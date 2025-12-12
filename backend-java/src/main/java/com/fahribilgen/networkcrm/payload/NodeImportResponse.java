package com.fahribilgen.networkcrm.payload;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class NodeImportResponse {
    private int processed;
    private int created;
    private int skipped;
    private List<String> errors;
}
