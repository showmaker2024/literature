# OpenFSI 输入参数说明

这份文档总结了 OpenFSI 在 3D 红细胞算例里最常用、最值得优先关注的输入参数，以及常见的调参思路。

## 输入分层

OpenFSI 的输入大体可以分成三层：

1. `param.xml`
   控制流体计算域、流动类型、输出频率和耦合方式。
2. `in.*`
   控制 LAMMPS 侧的结构求解、邻域参数、时间步长、诊断输出和轨迹输出。
3. `*.data`
   存放红细胞模型本身的几何、连接关系和膜力学系数。

实际使用时，建议优先改前两层；只有在你明确要修改红细胞材料模型时，再去改 `.data`。

## `param.xml`

示例文件： [example/3D/RBC_suspension/param.xml](/C:/OpenFSI/example/3D/RBC_suspension/param.xml:1)

### `geometry` 部分

- `Resolution`
  表示 Palabos 流体求解使用的格点分辨率标度。
  一般不要随便改，因为它会影响整个流场离散尺度和计算量。

- `Viscosity`
  流体粘度。
  粘度越大，流动越“黏”，红细胞形变通常更缓和，也更容易稳定。
  粘度越小，流动作用更强，但更容易出现数值不稳定。

- `x_length`, `y_length`, `z_length`
  流场计算域尺寸。
  应和 `.data` 文件中的盒子范围保持一致，或者至少兼容。
  如果想减少边界影响、增加红细胞之间的间距或加长通道，可以调大这些尺寸。

### `fluid` 部分

- `Shear_flag`
  是否开启简单剪切流。
  设为 `1` 表示开启。

- `Shear_Top_Velocity`, `Shear_Bot_Velocity`
  剪切流上、下边界速度。
  两者差值决定剪切强度。
  想让红细胞更容易产生明显形变，就优先增大这两个值的差。

- `Poiseuille_flag`
  是否开启 Poiseuille 流。
  设为 `1` 表示开启。

- `Poiseuille_bodyforce`
  Poiseuille 流的驱动力。
  只有在 `Poiseuille_flag = 1` 时才有意义。

- `Uniform_flag`
  是否开启匀速来流。

- `U_uniform`
  匀速来流速度。

做验证时，建议一次只开一种流动模式，不要把剪切流、Poiseuille 流和均匀来流混在一起。

### `simulation` 部分

- `Total_timestep`
  总耦合步数。
  建议逐步增加，例如：
  `100 -> 1000 -> 5000 -> 10000`

- `Output_fluid_file`
  每隔多少步输出一次流场 VTK 文件。
  数值越小，时间分辨率越高，但文件数量会迅速变多。

- `Output_check_file`
  每隔多少步输出一次 checkpoint。
  长算例建议保留，而且不宜太稀。

- `CouplingType`
  `1` 表示经典速度耦合 IBM。
  `2` 表示依赖 `fix fcm` 的力耦合路径。
  对于新算例验证，优先推荐 `1`，因为更简单，也更容易先跑通。

## `in.*`：LAMMPS 输入文件

示例文件： [example/3D/RBC_suspension/in.single_rbc_fsi](/C:/OpenFSI/example/3D/RBC_suspension/in.single_rbc_fsi:1)

### 基础设置

- `units`
  单位体系。
  必须和红细胞模型参数保持一致，不建议单独修改。

- `dimension`
  3D 红细胞算例保持为 `3`。

- `atom_style`
  当前红细胞算例使用 `molecular`。

- `boundary`
  粒子系统边界条件。
  `p p p` 是最常见的起点。
  如果要做上下有壁面的通道，可以在相应方向改成非周期边界。

- `processors`
  LAMMPS 的空间并行划分方式。
  一般尽量和 MPI 进程数及计算域长宽比例匹配。
  对于长通道，优先沿最长方向划分。

### 邻域和通信参数

- `neighbor`
  邻居表的 skin 距离。
  太小可能漏掉邻居，太大则会增加计算量。

- `neigh_modify delay 0 every 1`
  表示每步都更新邻居表。
  对红细胞膜这种持续运动的节点网络来说比较稳妥。

- `comm_modify cutoff`
  通信截断半径。
  这是稳定性里非常关键的一项。
  如果日志提示 communication cutoff 太短，应优先增大它。

### 相互作用与膜模型

- `pair_style`, `pair_coeff`
  非键相互作用设置。
  在单红细胞验证里，通常设得很弱，重点放在膜力学和流固耦合上。

- `bond_style wlc`
  膜的拉伸模型。

- `angle_style rbc`
  红细胞膜面积/体积相关的角势模型。

- `dihedral_style bend`
  红细胞膜弯曲刚度模型。

这些 style 必须和 `.data` 文件中的系数块类型一致，不能随意替换。

### 时间推进与输出

- `timestep`
  结构求解时间步长。
  这是最敏感的稳定性参数之一。
  如果算例不稳，通常先减小它。

- `dump`
  结构轨迹输出频率。
  值小更方便观察过程，但文件会变大。

- `compute` / `fix ave/time`
  可用于输出质心、包围盒等诊断量，方便检查运动和形变是否合理。

## `.data`：红细胞模型文件

示例文件： [example/3D/RBC_suspension/1rbc.data](/C:/OpenFSI/example/3D/RBC_suspension/1rbc.data:1)

`.data` 文件包含：

- 计算盒子范围
- 节点坐标
- 键连接关系和 `Bond Coeffs #wlc`
- 角连接关系和 `Angle Coeffs #rbc`
- 二面角连接关系和 `Dihedral Coeffs #bend`

只有在你明确想改红细胞模型本身时，才建议动这一层，例如：

- 改红细胞初始位置、初始朝向
- 改膜拉伸刚度
- 改弯曲刚度
- 改局部/整体面积与体积约束强度

这一层最“物理”，但也最容易把模型改坏，所以一般放在最后再动。

## 推荐调参顺序

### 如果目标是“先跑稳”

建议按下面顺序调：

1. 先减小 `timestep`
2. 再增大 `comm_modify cutoff`
3. 适当增大 `neighbor`
4. 降低流动强度

### 如果目标是“让红细胞更明显变形”

建议按下面顺序调：

1. 增大 `Shear_Top_Velocity / Shear_Bot_Velocity`
2. 增大 `Total_timestep`
3. 必要时再调整膜模型系数

### 如果目标是“减少边界影响”

建议优先：

1. 增大 `x_length`, `y_length`, `z_length`
2. 保证红细胞与边界之间留有足够缓冲区

### 如果目标是“提高 MPI 并行效率”

建议优先：

1. 根据计算域长宽比例选 MPI 进程数
2. 在 `processors` 中设置一致的划分
3. 优先沿最长方向做空间划分
