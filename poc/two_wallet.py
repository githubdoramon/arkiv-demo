"""Two-wallet Arkiv review proof. Run with `uv run python proof/two_wallet.py`."""

from __future__ import annotations

import os
import uuid

from arkiv import (
    Arkiv,
    CreationFlags,
    EntityMutationError,
    ExpirationTime,
    json_to_payload,
)

RPC = os.environ.get("ARKIV_RPC_URL", "http://127.0.0.1:18547")
EXPECTED_CHAIN_ID = 1337
AUTHOR_KEY = os.environ.get("AUTHOR_PRIVATE_KEY")
KEEPER_KEY = os.environ.get("KEEPER_PRIVATE_KEY")
if not AUTHOR_KEY or not KEEPER_KEY:
    raise SystemExit("Set AUTHOR_PRIVATE_KEY and KEEPER_PRIVATE_KEY to two funded test wallets.")
if AUTHOR_KEY == KEEPER_KEY:
    raise SystemExit("Use two different wallets.")


def passed(message: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(f"FAIL: {message}")
    print(f"PASS: {message}")


def main() -> None:
    # Verify the explicitly local chain before loading the two published dev-only keys into
    # signing clients or sending any transaction. Refuse every other chain id.
    probe = Arkiv(RPC)
    actual_chain_id = probe.web3.eth.chain_id
    probe.close()
    if actual_chain_id != EXPECTED_CHAIN_ID:
        raise SystemExit(
            f"Refusing to transmit local demo keys: expected chain {EXPECTED_CHAIN_ID}, "
            f"got {actual_chain_id} at {RPC}. Use only the disposable local devnode."
        )
    author = Arkiv(RPC, account=AUTHOR_KEY)
    keeper = Arkiv(RPC, account=KEEPER_KEY)
    tag = "review-proof-" + uuid.uuid4().hex[:12]
    try:
        print(f"Network chain id: {author.web3.eth.chain_id}")
        print(f"Author: {author.account.address}; keeper: {keeper.account.address}")

        # A regular native GLM transfer is possible. It funds the wallet; it is not a
        # separate fee payer and does not sign Arkiv content on behalf of its author.
        transfer_value = 1
        keeper_before_funding = author.web3.eth.get_balance(keeper.account.address)
        nonce = author.web3.eth.get_transaction_count(author.account.address)
        signed = author.account.sign_transaction({
            "chainId": EXPECTED_CHAIN_ID,
            "nonce": nonce,
            "to": keeper.account.address,
            "value": transfer_value,
            "gas": 21_000,
            "gasPrice": author.web3.eth.gas_price,
        })
        funding_tx = author.web3.eth.send_raw_transaction(signed.raw_transaction)
        funding_receipt = author.web3.eth.wait_for_transaction_receipt(funding_tx)
        passed("backend wallet can fund another wallet with a native test-token transfer", funding_receipt.status == 1 and author.web3.eth.get_balance(keeper.account.address) == keeper_before_funding + transfer_value)

        profile = author.create_entity(
            payload=json_to_payload({
                "schema": "profile/v1", "wallet": author.account.address,
                "display_name": "Writer",
                "logical_id": f"profile:{EXPECTED_CHAIN_ID}:{author.account.address.lower()}",
            }),
            content_type="application/json",
            attributes={"app": "arkiv-review-demo", "kind": "profile", "tag": tag,
                        "wallet": author.account.address,
                        "logical_id": f"profile:{EXPECTED_CHAIN_ID}:{author.account.address.lower()}"},
            expires=ExpirationTime.from_days(180),
        )
        author.patch_entity(profile.entity_key, payload=json_to_payload({
            "schema": "profile/v1", "wallet": author.account.address,
            "display_name": "Writer Two",
            "logical_id": f"profile:{EXPECTED_CHAIN_ID}:{author.account.address.lower()}",
        }))
        passed("profile owner can perform an authorized mutation", author.get_entity(profile.entity_key).to_json()["display_name"] == "Writer Two")
        unauthorized_profile_rejected = False
        try:
            keeper.patch_entity(profile.entity_key, payload=json_to_payload({"display_name": "Impersonator"}))
        except EntityMutationError:
            unauthorized_profile_rejected = True
        passed("non-owner cannot mutate an owner-controlled profile", unauthorized_profile_rejected)

        root = author.create_entity(
            payload=json_to_payload({
                "schema": "review-root/v1", "author": author.account.address,
                "game_id": tag, "platform": "pc",
                "logical_id": f"review:{EXPECTED_CHAIN_ID}:{author.account.address.lower()}:{tag}:pc",
            }),
            content_type="application/json",
            attributes={"app": "arkiv-review-demo", "kind": "review-root", "tag": tag,
                        "author": author.account.address, "game_id": tag, "platform": "pc",
                        "logical_id": f"review:{EXPECTED_CHAIN_ID}:{author.account.address.lower()}:{tag}:pc"},
            expires=ExpirationTime.from_days(180),
            flags=CreationFlags(readonly=True, permissionless_extension=True),
        )
        revision1 = author.create_entity(
            payload=json_to_payload({
                "schema": "review-revision/v1", "root_key": root.entity_key,
                "revision": 1, "previous_revision_key": None,
                "author": author.account.address, "rating_half_stars": 9,
                "text": "A proof review.", "logical_id": f"{root.entity_key}:revision:1",
            }),
            content_type="application/json",
            attributes={"app": "arkiv-review-demo", "kind": "review-revision", "tag": tag,
                        "root_key": root.entity_key, "revision": 1,
                        "rating_half_stars": 9,
                        "logical_id": f"{root.entity_key}:revision:1"},
            expires=ExpirationTime.from_days(180),
            flags=CreationFlags(readonly=True, permissionless_extension=True),
        )
        entity_root = author.get_entity(root.entity_key)
        revision_before = author.get_entity(revision1.entity_key)
        passed("root creator is the signing author wallet", entity_root.creator.lower() == author.account.address.lower())
        passed("root owner initially is the author wallet", entity_root.owner.lower() == author.account.address.lower())
        passed("root payload author matches immutable creator identity", entity_root.to_json()["author"].lower() == entity_root.creator.lower())
        passed("revision creator is the signing author wallet", revision_before.creator.lower() == author.account.address.lower())
        passed("revision payload author matches immutable creator identity", revision_before.to_json()["author"].lower() == revision_before.creator.lower())
        passed("revision is immutable and third-party renewable", revision_before.creation_flags.readonly and revision_before.creation_flags.permissionless_extension)

        unauthorized_rejected = False
        try:
            keeper.patch_entity(revision1.entity_key, payload=json_to_payload({"tampered": True}))
        except EntityMutationError:
            unauthorized_rejected = True
        passed("unauthorized keeper mutation is rejected", unauthorized_rejected)
        owner_readonly_rejected = False
        try:
            author.patch_entity(revision1.entity_key, payload=json_to_payload({"tampered": True}))
        except EntityMutationError:
            owner_readonly_rejected = True
        passed("owner cannot mutate a readonly revision", owner_readonly_rejected)

        # Any relative expiry counts from the current block; 210 days therefore moves the
        # 180-day revision's deadline forward. The keeper pays this transaction itself.
        keeper.extend_entity(revision1.entity_key, ExpirationTime.from_days(210))
        revision_after = author.get_entity(revision1.entity_key)
        passed("third-party keeper paid to extend expiry", revision_after.expires_at > revision_before.expires_at)
        passed("renewal left readonly payload unchanged", revision_after.to_json() == revision_before.to_json())

        revision2 = author.create_entity(
            payload=json_to_payload({
                "schema": "review-revision/v1", "root_key": root.entity_key, "revision": 2,
                "previous_revision_key": revision1.entity_key,
                "author": author.account.address, "rating_half_stars": 10,
                "text": "Updated proof review.", "logical_id": f"{root.entity_key}:revision:2",
            }),
            content_type="application/json",
            attributes={"app": "arkiv-review-demo", "kind": "review-revision", "tag": tag,
                        "root_key": root.entity_key, "revision": 2,
                        "rating_half_stars": 10,
                        "previous_revision_key": revision1.entity_key,
                        "logical_id": f"{root.entity_key}:revision:2"},
            expires=ExpirationTime.from_days(180),
            flags=CreationFlags(readonly=True, permissionless_extension=True),
        )
        vote = keeper.create_entity(
            payload=json_to_payload({
                "schema": "review-vote/v1", "target_revision_key": revision1.entity_key,
                "voter": keeper.account.address, "value": "helpful",
                "logical_id": f"vote:{revision1.entity_key}:{keeper.account.address.lower()}",
            }),
            content_type="application/json",
            attributes={"app": "arkiv-review-demo", "kind": "review-vote", "tag": tag,
                        "target_revision_key": revision1.entity_key,
                        "voter": keeper.account.address,
                        "logical_id": f"vote:{revision1.entity_key}:{keeper.account.address.lower()}"},
            expires=ExpirationTime.from_days(180),
            flags=CreationFlags(readonly=True, permissionless_extension=True),
        )
        passed("edit is a new revision from original author", author.get_entity(revision2.entity_key).creator.lower() == author.account.address.lower())
        passed("vote stays bound to revision 1", keeper.get_entity(vote.entity_key).to_json()["target_revision_key"] == revision1.entity_key)

        # Transfer demonstrates current ownership can differ without erasing creator identity.
        author.change_ownership(root.entity_key, keeper.account.address)
        transferred = keeper.get_entity(root.entity_key)
        passed("ownership transfer changes owner but preserves creator", transferred.owner.lower() == keeper.account.address.lower() and transferred.creator.lower() == author.account.address.lower())

        print(f"ROOT={root.entity_key}")
        print(f"REVISION_1={revision1.entity_key}")
        print(f"REVISION_2={revision2.entity_key}")
        print(f"VOTE={vote.entity_key}")
        print("Proof complete. Test-chain entities expire and this demo does not claim permanent history.")
    finally:
        author.close()
        keeper.close()


if __name__ == "__main__":
    main()
