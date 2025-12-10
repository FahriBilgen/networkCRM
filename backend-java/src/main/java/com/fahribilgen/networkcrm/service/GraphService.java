package com.fahribilgen.networkcrm.service;

import com.fahribilgen.networkcrm.entity.User;
import com.fahribilgen.networkcrm.payload.GraphResponse;
import com.fahribilgen.networkcrm.payload.VisionTreeResponse;

public interface GraphService {
    GraphResponse getGraph(User user);
    VisionTreeResponse getVisionTree(User user);
}
