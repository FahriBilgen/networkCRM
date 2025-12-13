package com.fahribilgen.networkcrm.repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import com.fahribilgen.networkcrm.entity.Edge;
import com.fahribilgen.networkcrm.enums.EdgeType;

@Repository
public interface EdgeRepository extends JpaRepository<Edge, UUID> {

    List<Edge> findBySourceNodeId(UUID sourceNodeId);

    List<Edge> findByTargetNodeId(UUID targetNodeId);

    @Query("SELECT e FROM Edge e WHERE e.sourceNode.user.id = :userId")
    List<Edge> findBySourceNode_User_Id(@Param("userId") UUID userId);

    List<Edge> findBySourceNodeIdAndType(UUID sourceNodeId, EdgeType type);

    Optional<Edge> findFirstBySourceNodeIdAndTargetNodeIdAndType(UUID sourceNodeId, UUID targetNodeId, EdgeType type);
}
