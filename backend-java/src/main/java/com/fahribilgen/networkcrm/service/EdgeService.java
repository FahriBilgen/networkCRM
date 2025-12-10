package com.fahribilgen.networkcrm.service;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.EdgeRequest;
import com.fahribilgen.networkcrm.payload.EdgeResponse;

import java.util.List;
import java.util.UUID;

public interface EdgeService {
    EdgeResponse createEdge(EdgeRequest edgeRequest, User user);
    void deleteEdge(UUID edgeId, User user);
    List<EdgeResponse> getEdgesForNode(UUID nodeId, User user);
}
