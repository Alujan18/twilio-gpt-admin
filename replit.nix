{pkgs}: {
  deps = [
    pkgs.redis
    pkgs.openssl
    pkgs.postgresql
  ];
}
