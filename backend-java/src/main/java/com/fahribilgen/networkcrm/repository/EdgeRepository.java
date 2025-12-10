package com.fahribilgen.networkcrm.repository;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.enums.EdgeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface EdgeRepository extends JpaRepository<Edge, UUID> {
    List<Edge> findBySourceNodeId(UUID sourceNodeId);
    List<Edge> findByTargetNodeId(UUID targetNodeId);
    List<Edge> findBySourceNode_User_Id(UUID userId);
    List<Edge> findBySourceNodeIdAndType(UUID sourceNodeId, EdgeType type);
    Optional<Edge> findFirstBySourceNodeIdAndTargetNodeIdAndType(UUID sourceNodeId, UUID targetNodeId, EdgeType type);
}
